cmake_minimum_required(VERSION 3.0)

project(interference)

if (CMAKE_VERSION VERSION_LESS "3.1")
  if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set (CMAKE_CXX_FLAGS "--std=c++11 ${CMAKE_CXX_FLAGS}")
  else ()
    message(FATAL_ERROR "Unknown compiler version ${CMAKE_CXX_COMPILER_ID}.")
  endif ()
else ()
  set (CMAKE_CXX_STANDARD 11)
endif ()

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
