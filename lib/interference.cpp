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

#include "nlohmann/json.hpp"

using json = nlohmann::json;

std::string PREFIX;
std::string sched;
std::string output_format;
std::vector<int> affinity;
int localid;
int ranks;
bool mvapich_hack = false;

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

  auto localid_name_ptr = std::getenv("INTERFERENCE_LOCALID");
  if (localid_name_ptr) {
    auto localid_ptr = std::getenv(localid_name_ptr);
    if (!localid_ptr)
      throw std::runtime_error("INTERFERENCE_LOCALID points to nonexistent variable");
    localid = std::stol(localid_ptr);
  } else {
    // Probably this concept makes no sense in here
    localid = 0;
  }

  auto output_format_ptr = std::getenv("INTERFERENCE_OUTPUT");
  if (output_format_ptr) {
    output_format = std::string(output_format_ptr);
    if (output_format != "json" && output_format != "csv")
      throw std::runtime_error("INTERFERENCE_OUTPUT requests unknown format");
  } else {
    output_format = "csv";
  }

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
    gather_longs(diff_long, _values.data());
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
    _values.resize(_ranks);
    gather_longs(diff.count(), _values.data());
  }
};

class CPUaccounter : public SingleCounter<long> {
public:
  using SingleCounter<long>::SingleCounter;

  void start_accounting() {
    if (sched == "pinned") {
      _value = affinity[localid % affinity.size()];
      set_own_affinity(_value);
    } else if (sched == "cfs") {
      _value = -1;
      set_own_affinity(affinity);
    }
  }
};

class LocalId : public SingleCounter<long> {
public:
  using SingleCounter<long>::SingleCounter;

  void start_accounting() {
    _value = localid;
  }
};

class HostNameAccounter : public SingleCounter<std::string> {
public:
  using SingleCounter<std::string>::SingleCounter;

  void start_accounting() {
    // Assume no overflow happens
    _value.resize(name_len);
    gethostname(_value.data(), name_len);
    _value[name_len - 1] = '\0';
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
public:
  InterferenceAccounter(int ranks) :
    Accounter(ranks)
  {
    typedef std::unique_ptr<Counter> counter_ptr;
    _counters.push_back(counter_ptr(new IterAccounter(ranks, "ITER")));
    _counters.push_back(counter_ptr(new HostNameAccounter(ranks, "NODE")));
    _counters.push_back(counter_ptr(new LocalId(ranks, "LOCALID")));
    _counters.push_back(counter_ptr(new CPUaccounter(ranks, "CPU")));
    _counters.push_back(counter_ptr(new WallClock(ranks, "WTIME")));
    _counters.push_back(counter_ptr(new ProcReader(ranks, "UTIME")));
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
      j.push_back(row);
    }

    std::cout << j.dump() << std::endl;
  }

  void dump(const std::string &output, const std::set<std::string> &filter = std::set<std::string>()) {
    int my_rank = get_my_rank();
    if (my_rank != 0)
      return;

    auto map = generate_map(filter);

    if (output == "csv") {
      dump_csv(map);
    } else if (output == "json") {
      dump_json(map);
    } else {
      throw std::runtime_error("Unknown output format: " + output);
    }
  }
};

std::unique_ptr<InterferenceAccounter> accounter;

void interference_start()
{
  parse_env();

  ranks = get_ranks();

  accounter = std::unique_ptr<InterferenceAccounter>(new InterferenceAccounter(ranks));
  accounter->start_accounting();
}

void interference_end()
{
  // Here we should read stat
  accounter->end_accounting();

  accounter->dump(output_format);

  if (mvapich_hack) {
    barrier();
    std::flush(std::cout);
    exit(0);
  }
}
