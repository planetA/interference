#pragma once

#include "counter.hpp"

#include <unistd.h>
#include <regex>
#include <iostream>


static std::vector<int> parse_affinity(const std::string &cpu_string)
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

    if (!what[2].matched)
      break;

    start = what[2].first;
    if (*start == ',')
      start++;
  }

  std::sort(cpus.begin(), cpus.end());
  cpus.erase(std::unique(cpus.begin(), cpus.end()), cpus.end());

  return cpus;
}

class CpuManager : public SingleCounter<long>
{
private:
  int _localid;
  int _block_size;
  std::string _sched;
  std::vector<int> _affinity;

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

public:
  CpuManager(int ranks, const std::string &name)
    : SingleCounter(ranks, name),
      _localid(get_indirect_param("INTERFERENCE_LOCALID")),
      _block_size(get_indirect_param("INTERFERENCE_LOCAL_SIZE"))
  {
    // Figure out which scheduler we are using
    auto sched_ptr = std::getenv("INTERFERENCE_SCHED");
    if (!sched_ptr)
      throw std::runtime_error("INTERFERENCE_SCHED should be set");
    _sched = std::string(sched_ptr);

    // Check that block size is set if scheduler is pinned_blocked,
    // because this scheduler requires block_size to be set
    if ((_block_size == 0) && (_sched == "pinned_blocked")) {
      throw std::runtime_error("Scheduler pinned_blocked requires variable"
                               " INTERFERENCE_LOCAL_SIZE to be set");
    }

    // Get affinity string
    auto affinity_ptr = std::getenv("INTERFERENCE_AFFINITY");
    if (!affinity_ptr)
      throw std::runtime_error("INTERFERENCE_AFFINITY should be set");
    _affinity = parse_affinity(affinity_ptr);
  }

  void start_accounting() {
    if (_sched == "pinned_blocked") {
      _value = _affinity[_localid * _affinity.size() / _block_size];
      set_own_affinity(_value);
    } else if (_sched == "pinned_cyclic") {
      _value = _affinity[_localid % _affinity.size()];
      set_own_affinity(_value);
    } else if (_sched == "cfs") {
      _value = -1;
      set_own_affinity(_affinity);
    } else {
      throw std::runtime_error("Unknown scheduler requested: " + _sched);
    }
  }
};
