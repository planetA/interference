#include <mpi.h>

#include "interference_mpi.h"

int get_ranks()
{
  int ranks;
  MPI_Comm_size(MPI_COMM_WORLD, &ranks);
  return ranks;
}

int get_my_rank()
{
  int my_rank;
  MPI_Comm_rank(MPI_COMM_WORLD, &my_rank);
  return my_rank;
}

void gather_times(long my_time, long* times)
{
  MPI_Gather(&my_time, 1, MPI_LONG, times, 1, MPI_LONG, 0, MPI_COMM_WORLD);
}

void gather_names(const char *my_name, char *names, unsigned name_len)
{
  MPI_Gather((void *)my_name, name_len, MPI_CHAR, names, name_len, MPI_CHAR, 0, MPI_COMM_WORLD);
}

void barrier()
{
  MPI_Barrier(MPI_COMM_WORLD);
}
