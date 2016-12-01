#include <vector>
#include <string>
#include <cassert>

#include "counters/cpumanager.hpp"

void cpu_list_test()
{
  {
    std::vector<int> cpus = parse_affinity("3");

    assert(cpus.size() == 1);
    assert(cpus == std::vector<int>{3});
  }

  {
    std::vector<int> cpus = parse_affinity("5-8");

    assert(cpus.size() == 4);
    assert((cpus == std::vector<int>{5, 6, 7, 8}));
  }

  {
    std::vector<int> cpus = parse_affinity("3,5,6");

    assert(cpus.size() == 3);
    assert((cpus == std::vector<int>{3, 5, 6}));
  }

  {
    std::vector<int> cpus = parse_affinity("3-5,6-7,9-12");

    assert(cpus.size() == 9);
    assert((cpus == std::vector<int>{3, 4, 5, 6, 7, 9, 10, 11, 12}));
  }

  {
    std::vector<int> cpus = parse_affinity("3-5,1,6-7,9-12,15");

    assert(cpus.size() == 11);
    assert((cpus == std::vector<int>{1, 3, 4, 5, 6, 7, 9, 10, 11, 12, 15}));
  }

  {
    std::vector<int> cpus = parse_affinity("3-5,1,5-6,3-7,15");

    assert(cpus.size() == 7);
    assert((cpus == std::vector<int>{1, 3, 4, 5, 6, 7, 15}));
  }

  {
    std::vector<int> cpus = parse_affinity("4-11,16-23");

    assert(cpus.size() == 16);
    assert((cpus == std::vector<int>{4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19, 20, 21, 22, 23}));
  }
}


int main(int argc, char **argv)
{
  cpu_list_test();
}
