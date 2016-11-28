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

void gather(void *my_data, size_t count, void *all_data)
{
  MPI_Gather(my_data,  count, MPI_BYTE,
             all_data, count, MPI_BYTE,
             0, MPI_COMM_WORLD);
}

void gather_names(const char *my_name, char *names, unsigned name_len)
{
  MPI_Gather((void *)my_name, name_len, MPI_CHAR, names, name_len, MPI_CHAR, 0, MPI_COMM_WORLD);
}

void barrier()
{
  MPI_Barrier(MPI_COMM_WORLD);
}
