install(PROGRAMS interference.py DESTINATION scripts)
install(DIRECTORY manager DESTINATION scripts
  FILES_MATCHING PATTERN "*.py")
