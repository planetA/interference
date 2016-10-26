#include "interference.h"

{{fn init MPI_Init}}
  {{callfn}}
  interference_start();
{{endfn}}

{{fn final MPI_Finalize}}
  interference_end();
  {{callfn}}
{{endfn}}