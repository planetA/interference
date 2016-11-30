#pragma once

#include <map>
#include <string>
#include <vector>
#include <chrono>
#include <memory>
#include <set>

#include "interference_mpi.h"

typedef std::map<std::string, std::vector<std::string>> CounterMap;

class Counter {
protected:
  std::string _name;
  virtual void exchange() = 0;

public:

  Counter(const std::string &name) : _name(name) {}

  const std::string name() { return _name; }

  virtual void start_accounting() = 0;
  virtual void end_accounting() = 0;

  virtual CounterMap emit() = 0;
};

typedef std::chrono::time_point<std::chrono::system_clock> wall_time_t;
typedef std::chrono::duration<long,std::milli> milli_time_t;

template<typename T>
class IntervalCounter : public Counter {
protected:
  T start, end;

  int _ranks;
  std::vector<long> _values;

public:
  IntervalCounter(int ranks, std::string name) :
    Counter(name),
    _ranks(ranks)
  {
  }

  void start_accounting() {
    get_value(start);
  }
  void end_accounting() {
    get_value(end);
    exchange();
  }

  CounterMap emit() {
    CounterMap map;
    std::vector<std::string> str_values;
    for (auto v : _values) {
      str_values.push_back(std::to_string(v));
    }
    map[_name] = str_values;
    return map;
  }

protected:
  virtual void get_value(T &) = 0;
};


template<typename T>
class SingleCounter : public Counter {
protected:
  T _value;

  int _ranks;
  std::vector<T> _values;

public:
  SingleCounter(int ranks, const std::string &name) :
    Counter(name),
    _ranks(ranks)
  {
  }

  CounterMap emit() {
    CounterMap map;
    std::vector<std::string> str_values;
    for (auto v : _values) {
      str_values.push_back(std::to_string(v));
    }
    map[_name] = str_values;
    return map;
  }

  void start_accounting() {}
  void end_accounting() {
    exchange();
  }

protected:
  void exchange() {
    _values.resize(_ranks);
    gather(&_value, sizeof(long), _values.data());
  }
};

class Accounter {
protected:
  std::vector<std::unique_ptr<Counter>> _counters;
  int _ranks;
public:
  Accounter(int ranks) : _ranks(ranks) {};

  void start_accounting() {
    for (const auto &c : _counters)
      c->start_accounting();
  }

  void end_accounting() {
    for (const auto &c : _counters)
      c->end_accounting();
  }

  CounterMap generate_map(const std::set<std::string> &filter) {
    CounterMap results;

    for (const auto &c : _counters) {
      // If filter non-empty and key is in filter, skip it
      if (filter.size() > 0 && filter.find(c->name()) != filter.end())
        continue;

      CounterMap counter_data = c->emit();

      results.insert(counter_data.begin(), counter_data.end());
    }

    return results;
  }
};
