#pragma once

#include "counter.hpp"

class PerfCounter : public SingleCounter<uint64_t>
{
  int _fd;

  void build_perf_attr(struct perf_event_attr *attr, const std::string &event);

public:

  PerfCounter(int ranks, std::string name);

  void start_accounting();
  void end_accounting();
};
