#include <cstdlib>
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <sstream>
#include <iterator>
#include <regex>
#include <chrono>

#include <unistd.h>
#include <sched.h>

#include "interference.h"
#include "interference_mpi.h"

std::string PREFIX;
std::string sched;
std::vector<int> affinity;
int localid;
int working_cpu;
bool mvapich_hack = false;

std::chrono::time_point<std::chrono::system_clock> start, end;

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

void interference_start()
{
  parse_env();

  if (sched == "pinned") {
    working_cpu = affinity[localid % affinity.size()];
    set_own_affinity(working_cpu);
  } else if (sched == "cfs") {
    working_cpu = -1;
    set_own_affinity(affinity);
  }

  start = std::chrono::system_clock::now();
}

static std::vector<std::string> get_stat_strings()
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

void interference_end()
{
  end = std::chrono::system_clock::now();

  auto wtime = end - start;
  // Here we should read stat
  std::vector<std::string> tokens = get_stat_strings();

  std::chrono::duration<long,std::milli> utime(std::stol(tokens[13]) * 1000 / sysconf(_SC_CLK_TCK));

  int ranks = get_ranks();
  std::vector<long> utimes(ranks);
  gather_times(std::chrono::duration_cast<std::chrono::milliseconds>(utime).count(), utimes.data());

  std::vector<long> wtimes(ranks);
  gather_times(std::chrono::duration_cast<std::chrono::milliseconds>(wtime).count(), wtimes.data());

  // Assume no overflow happens
  const unsigned name_len = 20;
  char name[name_len];
  gethostname(name, name_len);
  name[name_len - 1] = '\0';
  std::vector<char> names(ranks*name_len);
  gather_names(name, names.data(), name_len);


  int my_rank = get_my_rank();

  if (my_rank == 0) {
    for (int i = 0; i < ranks; i ++) {
      std::cout << PREFIX
                << " ,RANK: " << i
                << " ,ITER: " << 1
                << " ,CPU: " << working_cpu
                << " ,LOCALID: " << localid
                << " ,NODE: " << &names[i*name_len]
                << " ,WTIME: " << wtimes[i]
                << " ,UTIME: " << utimes[i] << std::endl;
    }
  }

  if (mvapich_hack) {
    barrier();
    std::flush(std::cout);
    exit(0);
  }
}
