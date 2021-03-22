# the compiler: gcc for C program, define as g++ for C++
GCC = gcc
GXX = g++

# Environments
CFLAGS  = -g -O3 -I. $(DEFINES)

# the build levenshtein target executable:
SHARED_STR_TARGET = shared_str
SHARED_STR_TARGET_FILE = liblevenshtein.so
EXE_STR_TARGET = exe_str
EXE_STR_TARGET_FILE = levenshtein
STR_OBJ = levenshtein.o
IN_STR_FILE = levenshtein.c

all: $(SHARED_STR_TARGET) $(EXE_STR_TARGET)

$(SHARED_STR_TARGET):
	$(GCC) -fPIC $(CFLAGS) -c $(IN_STR_FILE) -o $(STR_OBJ)
	$(GCC) -shared $(CFLAGS) -o $(SHARED_STR_TARGET_FILE) $(STR_OBJ)
	$(RM) $(STR_OBJ)

$(EXE_STR_TARGET):
	$(GCC) -fPIC $(CFLAGS) -c $(IN_STR_FILE) -o $(STR_OBJ)
	$(GCC) $(CFLAGS) -o $(EXE_STR_TARGET_FILE) $(STR_OBJ)
	$(RM) $(STR_OBJ)

clean:
	$(RM) $(SHARED_STR_TARGET_FILE) $(EXE_STR_TARGET_FILE)
