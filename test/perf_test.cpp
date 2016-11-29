#include "perf.hpp"

#include <iostream>

#include <unistd.h>

class MyPerfCounter : public PerfCounter
{
protected:
  using PerfCounter::PerfCounter;

  void exchange() override {_values.push_back(_value);}
};

int main(int argc, char **argv)
{
  MyPerfCounter cnt(1, "migrations");

  cnt.start_accounting();
  for (int i = 0; i < 100; i++) {
    double res = 1.0+i;
    for (int j = 0; j < 10000000; j++) {
      if (argc + res == -1) {
        res += 2.;
      } else {
        res *= 1.001;
      }
    }
    usleep(1000);
  }
  cnt.end_accounting();
  CounterMap map = cnt.emit();
  for (const auto &i : map) {
    std::cout << i.first << ": ";
    for (const auto &j : i.second)
      std::cout << j << " ";
    std::cout << std::endl;
  }
  return 0;
}
