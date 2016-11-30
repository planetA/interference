#include <cstdlib>
#include <iostream>
#include <fstream>
#include <vector>
#include <set>
#include <string>
#include <sstream>
#include <iterator>
#include <regex>
#include <chrono>

#include <unistd.h>
#include <sched.h>

#include "interference.h"
#include "interference_mpi.h"
#include "counter.hpp"
#include "perf.hpp"

#include "nlohmann/json.hpp"

using json = nlohmann::json;

std::string PREFIX;
std::string sched;
std::vector<int> affinity;
bool mvapich_hack = false;

/**
 * Parse integer value from an environment variable, which
 * environment variable ~reference~ references.
 * @param reference environment variable with environment variable name
 * @return value of the indirectly referenced variable
 */
static int get_indirect_param(const std::string &reference)
{
  int res = 0;
  auto ref_ptr = std::getenv(reference.c_str());
  if (ref_ptr) {
    auto param_ptr = std::getenv(ref_ptr);
    if (!param_ptr)
      throw std::runtime_error(reference +
                               " points to nonexistent variable");
    res = std::stol(param_ptr);
  }

  return res;
}

std::vector<int> parse_affinity(std::string cpu_string)
{
  std::vector<int> cpus;
  // static boost::regex r("(\\d+|\\d+-\\d+)?");
  std::regex r("^(\\d+-\\d+|\\d+)(,\\d+-\\d+|,\\d+)?(,\\d+-\\d+|,\\d+)*$");

  // Do regex match and convert the interesting part to
  // int.
  std::smatch what;
  if (!std::regex_match(cpu_string, what, r)) {
    throw std::runtime_error("Can't parse CPU string");
  }

  std::string::const_iterator start = cpu_string.begin();
  std::string::const_iterator end = cpu_string.end();

  while (std::regex_search(start, end, what, r)) {
    // what[1] single or a range of cpus
    if (!what[1].matched)
      throw std::runtime_error("Can't parse CPU string");

    std::string stest(what[1].first, what[1].second);
    auto minus = stest.find('-');
    if (minus == std::string::npos) {
      int value;
      try {
        value = std::stoi(stest);
      } catch (std::exception &e) {
        throw std::runtime_error("Can't parse CPU string");
      }
      cpus.push_back(value);
    } else {
      auto s = std::stoi(stest.substr(0, minus));
      auto e = std::stoi(stest.substr(minus+1));

      if (s > e)
        throw std::runtime_error("Can't parse CPU string");

      for (int cpu = s; cpu<=e; cpu++)
        cpus.push_back(cpu);
    }
    start = what[2].first;
    if (*start == ',')
      start++;
  }

  std::sort(cpus.begin(), cpus.end());
  cpus.erase(std::unique(cpus.begin(), cpus.end()), cpus.end());

  return cpus;
}

void parse_env()
{
  // Here we should set scheduler
  auto env = std::getenv("INTERFERENCE_PREFIX");
  if (!env)
    throw std::runtime_error("INTERFERENCE_PREFIX should be set");
  PREFIX = env;

  auto sched_ptr = std::getenv("INTERFERENCE_SCHED");
  if (!sched_ptr)
    throw std::runtime_error("INTERFERENCE_SCHED should be set");
  sched = std::string(sched_ptr);

  auto affinity_ptr = std::getenv("INTERFERENCE_AFFINITY");
  if (!affinity_ptr)
    throw std::runtime_error("INTERFERENCE_AFFINITY should be set");
  affinity = parse_affinity(affinity_ptr);

  if (std::getenv("INTERFERENCE_HACK"))
    mvapich_hack = true;
}

/**
 *  Set affinity to a particular cpu
 */
static void set_own_affinity(const cpu_set_t &cpu_set)
{
  int ret = sched_setaffinity(getpid(), sizeof(cpu_set), &cpu_set);
  if (ret)
    throw std::runtime_error("Failed to set affinity");
}

static void set_own_affinity(int cpu)
{
  cpu_set_t cpu_set;

  CPU_ZERO(&cpu_set);
  CPU_SET(cpu, &cpu_set);
  set_own_affinity(cpu_set);
}

static void set_own_affinity(const std::vector<int> &cpus)
{
  cpu_set_t cpu_set;

  CPU_ZERO(&cpu_set);
  for (auto c : cpus)
    CPU_SET(c, &cpu_set);
  set_own_affinity(cpu_set);
}


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

public:
  using IntervalCounter<milli_time_t>::IntervalCounter;

  void get_value(milli_time_t &val) {
    std::vector<std::string> tokens = get_stat_strings();

    val = milli_time_t(std::stol(tokens[13]) * 1000 / sysconf(_SC_CLK_TCK));
  }

  void exchange() {
    auto diff = end - start;
    long diff_long = diff.count();
    _values.resize(_ranks);
    gather(&diff_long, sizeof(diff_long), _values.data());
  }
};

class CPUaccounter : public SingleCounter<long> {
  int localid;
  int block_size;
public:
  CPUaccounter(int ranks, const std::string &name)
    : SingleCounter(ranks, name),
      localid(get_indirect_param("INTERFERENCE_LOCALID")),
      block_size(get_indirect_param("INTERFERENCE_LOCAL_SIZE"))
  {
    if ((block_size == 0) && (sched == "pinned_blocked")) {
      throw std::runtime_error("Scheduler pinned_blocked requires variable"
                               " INTERFERENCE_LOCAL_SIZE to be set");
    }
  }

  void start_accounting() {
    if (sched == "pinned_blocked") {
      _value = affinity[localid * affinity.size() / block_size];
      std::cout << localid << " " << block_size << std::endl;
      set_own_affinity(_value);
    } else if (sched == "pinned_cyclic") {
      _value = affinity[localid % affinity.size()];
      set_own_affinity(_value);
    } else if (sched == "cfs") {
      _value = -1;
      set_own_affinity(affinity);
    } else {
      throw std::runtime_error("Unknown scheduler requested: " + sched);
    }
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
    _counters.push_back(counter_ptr(new CPUaccounter(ranks, "CPU")));
    _counters.push_back(counter_ptr(new WallClock(ranks, "WTIME")));
    _counters.push_back(counter_ptr(new ProcReader(ranks, "UTIME")));

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
  parse_env();

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

  if (mvapich_hack) {
    barrier();
    std::flush(std::cout);
    exit(0);
  }
}
