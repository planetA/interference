set(test_np "4"  CACHE STRING "Parallelism level for testing.")

find_package(MPI REQUIRED)
include_directories(${MPI_C_INCLUDE_PATH})
include_directories(${PROJECT_SOURCE_DIR}/lib)

SET(CMAKE_C_COMPILER mpicc)
SET(CMAKE_CXX_COMPILER mpicxx)
set(CMAKE_CXX_COMPILE_FLAGS ${CMAKE_CXX_COMPILE_FLAGS} ${MPI_COMPILE_FLAGS})
set(CMAKE_CXX_LINK_FLAGS ${CMAKE_CXX_LINK_FLAGS} ${MPI_LINK_FLAGS})


function(add_mpi_test test_name test_source)
  add_executable(${test_name} ${test_source})
  target_link_libraries(${test_name} interference ${MPI_C_LIBRARIES})
  add_test(${test_name} ${test_name} COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} ${test_np} ${test_name})
  set_property(TEST ${test_name} PROPERTY ENVIRONMENT
    "INTERFERENCE_PREFIX=INTERFERENCE"
    "INTERFERENCE_SCHED=cfs"
    "INTERFERENCE_AFFINITY=3"
    "INTERFERENCE_TESTID=4"
    "INTERFERENCE_LOCALID=INTERFERENCE_TESTID")
endfunction(add_mpi_test)

add_mpi_test(init_test_xx init_test.cpp)
add_mpi_test(init_test init_test.c)

add_executable(cpu_list_test cpu_list_test.cpp)
target_link_libraries(cpu_list_test interference)
add_test(cpu_list_test cpu_list_test)

add_executable(perf_test perf_test.cpp)
target_link_libraries(perf_test interference)
add_test(perf_test perf_test)
