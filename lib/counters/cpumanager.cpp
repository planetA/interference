#include <unistd.h>
#include <regex>
#include <iostream>
#include <cassert>

#include <sched.h>
#include <unistd.h>
#include <sys/resource.h>

#include "cpumanager.hpp"

std::vector<int> parse_affinity(const std::string &cpu_string)
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

static void scheduler_set(pid_t pid, int policy, int priority)
{
  struct sched_param param;
  memset(&param, 0, sizeof(param));

  int min = sched_get_priority_min(policy);
  int max = sched_get_priority_max(policy);

  // Max reserved for the scheduler itself
  priority = std::min(priority + min - 1, max - 1);

  int resource;
  if (policy == SCHED_FIFO) {
    resource = RLIMIT_RTPRIO;
  } else if (policy == SCHED_OTHER) {
    resource = RLIMIT_NICE;
  } else {
    throw std::runtime_error(std::string("Unknown scheduling policy requested") +
                             std::to_string(policy));
  }

  struct rlimit rlim;
  int ret = getrlimit(resource, &rlim);
  assert(ret == 0);

  // cast from long long to int is safe, because values are up to 99
  priority = std::min(priority, static_cast<int>(rlim.rlim_max));
  std::cout << pid << "  " << policy << "  " << priority << "  " << rlim.rlim_cur << "  " << rlim.rlim_max << " | " << max << "  " << min <<std::endl;
  // std::cout << pid << "  " << policy << "  " << priority << std::endl;

  param.sched_priority = priority;
  ret = sched_setscheduler(pid, policy, &param);

  if (ret) {
    throw std::runtime_error(std::string("Failed to set priority: ") +
                             std::strerror(errno));
  }
}

CpuManager::CpuManager(int ranks, const std::string &name)
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

void CpuManager::start_accounting()
{
  if (_sched == "pinned_blocked") {
    _value = _affinity[_localid * _affinity.size() / _block_size];
    set_own_affinity(_value);
  } else if (_sched == "pinned_cyclic") {
    _value = _affinity[_localid % _affinity.size()];
    set_own_affinity(_value);
  } else if (_sched == "cfs") {
    _value = -1;
    set_own_affinity(_affinity);
  } else if (_sched == "fifo_blocked") {
    _value = _affinity[_localid * _affinity.size() / _block_size];
    set_own_affinity(_value);
    scheduler_set(0, SCHED_FIFO, 1);
  } else if (_sched == "fifo_cyclic") {
    _value = _affinity[_localid % _affinity.size()];
    set_own_affinity(_value);
    scheduler_set(0, SCHED_FIFO, 1);
  } else {
    throw std::runtime_error("Unknown scheduler requested: " + _sched);
  }
}

void CpuManager::end_accounting()
{
  if ((_sched == "fifo_blocked") || (_sched == "fifo_cyclic")) {
    scheduler_set(0, SCHED_FIFO, 1);
  }
  exchange();
}
