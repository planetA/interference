#include <unistd.h>
#include <string.h>
#include <sys/ioctl.h>
#include <linux/perf_event.h>
#include <asm/unistd.h>

#include "perf.hpp"
#include "interference_mpi.h"

// Copy paste from man page
static long
perf_event_open(struct perf_event_attr *hw_event, pid_t pid,
                int cpu, int group_fd, unsigned long flags)
{
  int ret;

  ret = syscall(__NR_perf_event_open, hw_event, pid, cpu,
                group_fd, flags);
  return ret;
}

void PerfCounter::build_perf_attr(struct perf_event_attr *attr,
                                  const std::string &event)
{
  memset(attr, 0, sizeof(struct perf_event_attr));

  if (event == "cpu_cycles") {
    attr->type   = PERF_TYPE_HARDWARE;
    attr->config = PERF_COUNT_HW_CPU_CYCLES;
  } else if (event == "instructions") {
    attr->type   = PERF_TYPE_HARDWARE;
    attr->config = PERF_COUNT_HW_INSTRUCTIONS;
  } else if (event == "cache_references") {
    attr->type   = PERF_TYPE_HARDWARE;
    attr->config = PERF_COUNT_HW_CACHE_REFERENCES;
  } else if (event == "cache_misses") {
    attr->type   = PERF_TYPE_HARDWARE;
    attr->config = PERF_COUNT_HW_CACHE_MISSES;
  } else if (event == "branch_instructions") {
    attr->type   = PERF_TYPE_HARDWARE;
    attr->config = PERF_COUNT_HW_BRANCH_INSTRUCTIONS;
  } else if (event == "branch_misses") {
    attr->type   = PERF_TYPE_HARDWARE;
    attr->config = PERF_COUNT_HW_BRANCH_MISSES;
  } else if (event == "migrations") {
    attr->type   = PERF_TYPE_SOFTWARE;
    attr->config = PERF_COUNT_SW_CPU_MIGRATIONS;
  } else if (event == "page_faults") {
    attr->type   = PERF_TYPE_SOFTWARE;
    attr->config = PERF_COUNT_SW_PAGE_FAULTS;
  } else if (event == "context_switches") {
    attr->type   = PERF_TYPE_SOFTWARE;
    attr->config = PERF_COUNT_SW_CONTEXT_SWITCHES;
  } else {
    throw std::runtime_error("Unknown perf event requested " + event);
  }

  attr->disabled = 1;
  attr->exclude_kernel = 1;
  attr->exclude_hv = 1;
  attr->size = sizeof(struct perf_event_attr);
}

PerfCounter::PerfCounter(int ranks, std::string name) :
  SingleCounter(ranks, name)
{
  struct perf_event_attr event;
  build_perf_attr(&event, name);

  _fd = perf_event_open(&event, 0, -1, -1, 0);
}

void PerfCounter::start_accounting()
{
  ioctl(_fd, PERF_EVENT_IOC_RESET, 0);
  ioctl(_fd, PERF_EVENT_IOC_ENABLE, 0);
}

void PerfCounter::end_accounting()
{
  ioctl(_fd, PERF_EVENT_IOC_DISABLE, 0);
  auto ret = read(_fd, &_value, sizeof(_value));
  if (ret != sizeof(_value)) {
    throw std::runtime_error("Failed to read counter: " + _name);
  }
  exchange();
}
