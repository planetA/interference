# wrap.py setup -- grab the add_wrapped_file macro.
set(WRAP ${PROJECT_SOURCE_DIR}/lib/wrap/wrap.py)
include(wrap/WrapConfig.cmake)

find_package(MPI REQUIRED)
include_directories(${MPI_C_INCLUDE_PATH})

set(CMAKE_INCLUDE_CURRENT_DIR ON)

if (fortran)
  add_wrapped_file(wrappers.c wrappers.w -f)
else()
  add_wrapped_file(wrappers.c wrappers.w)
endif()

if (wrapper)
  set(SOURCES interference.cpp interference_mpi.c wrappers.c perf.cpp)
  add_library(interference SHARED ${SOURCES})
  target_compile_definitions(interference PRIVATE PIC)
  set_property(TARGET interference PROPERTY POSITION_INDEPENDENT_CODE TRUE)
  target_link_libraries(interference ${MPI_C_LIBRARIES})
  install(TARGETS interference DESTINATION lib)
endif()

add_library(interference_static STATIC interference.cpp interference_mpi.c)
# target_link_libraries(interference_static ${MPI_C_LIBRARIES})
install(TARGETS interference_static DESTINATION lib)
