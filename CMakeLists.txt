cmake_minimum_required(VERSION 3.0)

if (CMAKE_VERSION VERSION_LESS "3.1")
  if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set (CMAKE_CXX_FLAGS "--std=gnu++11 ${CMAKE_CXX_FLAGS}")
  endif ()
else ()
  set (CMAKE_CXX_STANDARD 11)
endif ()

project(interference)

option(wrapper "Enable PMPI wrapper." ON)

add_subdirectory(lib)
add_subdirectory(scripts)

# Options. Turn on with 'cmake -Dtest=ON'.
option(test "Build all tests." OFF) # Makes boolean 'test' available.
option(fortran "Add fortran bindings." OFF) # Makes boolean 'test' available.

if (test AND wrapper)
  enable_testing()
  add_subdirectory(test)
endif()
