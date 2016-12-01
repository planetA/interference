#include <cstdlib>
#include <iostream>
#include <fstream>
#include <vector>
#include <set>
#include <string>
#include <sstream>
#include <iterator>
#include <chrono>

#include <sched.h>

#include "interference.h"
#include "interference_mpi.h"
#include "counter.hpp"
#include "perf.hpp"

#include "counters/cpumanager.hpp"

#include "nlohmann/json.hpp"

using json = nlohmann::json;

class WallClock : public IntervalCounter<wall_time_t> {
public:
  using IntervalCounter<wall_time_t>::IntervalCounter;

  void get_value(wall_time_t &val) {
    val = std::chrono::system_clock::now();
  }

  void exchange() {
    auto diff = end - start;
    long diff_long = std::chrono::duration_cast<std::chrono::milliseconds>(diff).count();

    _values.resize(_ranks);
    gather(&diff_long, sizeof(diff_long), _values.data());
  }
};

class ProcReader : public IntervalCounter<milli_time_t> {
  std::vector<std::string> get_stat_strings()
  {
    std::ifstream proc("/proc/self/stat");

    std::string line;
    std::getline(proc, line);
    std::istringstream iss(line);

    std::vector<std::string> tokens;
    std::copy(std::istream_iterator<std::string>(iss),
              std::istream_iterator<std::string>(),
              std::back_inserter(tokens));

    return tokens;
  }

  int _column;
public:
  using IntervalCounter<milli_time_t>::IntervalCounter;

  enum StatColumn
  {
    utime = 13,
    stime = 14,
  };

  ProcReader(StatColumn column, int ranks, const std::string &name) :
    IntervalCounter(ranks, name),
    _column(column)
  {}

  void get_value(milli_time_t &val) {
    std::vector<std::string> tokens = get_stat_strings();

    val = milli_time_t((std::stol(tokens[_column]) * 1000
                        / sysconf(_SC_CLK_TCK)));
  }

  void exchange() {
    auto diff = end - start;
    long diff_long = diff.count();
    _values.resize(_ranks);
    gather(&diff_long, sizeof(diff_long), _values.data());
  }
};

class LocalId : public SingleCounter<long> {
  int localid;
public:

  LocalId(int ranks, const std::string &name) :
    SingleCounter(ranks, name),
    localid(get_indirect_param("INTERFERENCE_LOCALID"))
  {}

  void start_accounting() {
    _value = localid;
  }
};

class HostNameAccounter : public Counter {
protected:
  std::vector<char> _value;

  int _ranks;
  std::vector<char> _values;
  const unsigned name_len;
public:
  HostNameAccounter(int ranks, std::string name, unsigned name_len = 20) :
    Counter(name),
    _ranks(ranks),
    name_len(name_len)
  {
  }

  CounterMap emit() {
    CounterMap map;
    std::vector<std::string> str_values;

    for (int i = 0; i < _ranks; i ++) {
      auto name = std::string(_values.data() + i * name_len);
      str_values.push_back(name);
    }

    map[_name] = str_values;
    return map;
  }

  void end_accounting() {
    exchange();
  }

  void start_accounting() {
    // Assume no overflow happens
    _value.resize(name_len);
    gethostname(_value.data(), name_len);
    _value[name_len - 1] = '\0';
  }

private:
  void exchange() {
    _values.resize(name_len * _ranks);
    gather_names(_value.data(), _values.data(), name_len);
  }

};

class IterAccounter : public SingleCounter<long> {
public:
  using SingleCounter<long>::SingleCounter;

  void start_accounting() {
    _value = 1;
  }
};


class InterferenceAccounter : public Accounter {
  const std::string output_format;
  std::string PREFIX;

private:
  typedef std::unique_ptr<Counter> counter_ptr;

  std::vector<std::string> parse_perf_counters(const std::string &str) {
    std::vector<std::string> result;
    std::stringstream ss(str);
    std::string token;

    while(std::getline(ss, token, ',')) {
      result.push_back(token);
    }

    return result;
  }

  void parse_and_add_perf_counters(const std::string &str) {
    std::vector<std::string> counter_list;
    counter_list = parse_perf_counters(str);

    if (counter_list.size() == 0)
      return;

    for (const auto &cnt : counter_list) {
      _counters.push_back(counter_ptr(new PerfCounter(_ranks, cnt)));
    }
  }

public:
  InterferenceAccounter(int ranks, const std::string &output_format) :
    Accounter(ranks), output_format(output_format)
  {
    _counters.push_back(counter_ptr(new IterAccounter(ranks, "ITER")));
    _counters.push_back(counter_ptr(new HostNameAccounter(ranks, "NODE")));
    _counters.push_back(counter_ptr(new LocalId(ranks, "LOCALID")));
    _counters.push_back(counter_ptr(new CpuManager(ranks, "CPU")));
    _counters.push_back(counter_ptr(new WallClock(ranks, "WTIME")));

    auto utime = ProcReader::StatColumn::utime;
    _counters.push_back(counter_ptr(new ProcReader(utime, ranks, "UTIME")));
    auto stime = ProcReader::StatColumn::stime;
    _counters.push_back(counter_ptr(new ProcReader(stime, ranks, "STIME")));

    if (output_format != "csv" && output_format != "json") {
      throw std::runtime_error("Unknown output format: " + output_format);
    }

    // Allow additional perf counters for json
    if (output_format == "json") {
      auto counters = std::getenv("INTERFERENCE_PERF");
      if (counters) {
        parse_and_add_perf_counters(counters);
      }
    }

    auto env = std::getenv("INTERFERENCE_PREFIX");
    if (!env)
      throw std::runtime_error("INTERFERENCE_PREFIX should be set");
    PREFIX = env;
  }

  void dump_csv(const CounterMap &map) {
    for (int i = 0; i < _ranks; i++) {
      std::cout << PREFIX
                << " ,RANK: " << i;
      for (const auto &cnt : map) {
        std::cout << " ," << cnt.first << ": "
                  << cnt.second[i];
      }
      std::cout << std::endl;
    }
  }

  void dump_json(const CounterMap &map) {
    json j;

    for (int i = 0; i < _ranks; i++) {
      json row;
      for (const auto &cnt : map) {
        row[cnt.first] = cnt.second[i];
      }
      j[PREFIX].push_back(row);
    }

    std::cout << j.dump() << std::endl;
  }

  void dump(const std::set<std::string> &filter = std::set<std::string>()) {
    int my_rank = get_my_rank();
    if (my_rank != 0)
      return;

    auto map = generate_map(filter);

    if (output_format == "csv") {
      dump_csv(map);
    } else if (output_format == "json") {
      dump_json(map);
    }
  }
};

std::unique_ptr<InterferenceAccounter> accounter;

void interference_start()
{
  int ranks = get_ranks();

  accounter = std::unique_ptr<InterferenceAccounter>(
    new InterferenceAccounter(ranks, std::getenv("INTERFERENCE_OUTPUT")));
  accounter->start_accounting();
}

void interference_end()
{
  // Here we should read stat
  accounter->end_accounting();

  accounter->dump();

  if (std::getenv("INTERFERENCE_HACK")) {
    barrier();
    std::flush(std::cout);
    exit(0);
  }
}
