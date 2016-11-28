#pragma once

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */

  int get_ranks();
  int get_my_rank();
  void gather(void *my_data, size_t count, void* all_count);
  void gather_names(const char *my_name, char *names, unsigned name_len);
  void barrier();

#ifdef __cplusplus
}
#endif /* __cplusplus */
