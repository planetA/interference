#pragma once

#include "counter.hpp"


class CpuManager : public SingleCounter<long>
{
private:
  int _localid;
  int _block_size;
  std::string _sched;
  std::vector<int> _affinity;

public:
  CpuManager(int, const std::string &);

  void start_accounting() override;
  void end_accounting() override;
};
