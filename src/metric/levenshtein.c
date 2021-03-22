#define MIN3(a, b, c) ((a) < (b) ? ((a) < (c) ? (a) : (c)) : ((b) < (c) ? (b) : (c)))
#include <string.h>
#include <stdio.h>

//#define DEBUG

int levenshtein(char *s1, char *s2) {
    unsigned int s1len, s2len, x, y, lastdiag, olddiag;
    s1len = strlen(s1);
    s2len = strlen(s2);
#ifdef DEBUG
    printf("s1 length %d, s2 length %d\n", s1len, s2len);
#endif
    unsigned int column[s1len+1];
    for (y = 1; y <= s1len; y++)
        column[y] = y;
    for (x = 1; x <= s2len; x++) {
        column[0] = x;
        for (y = 1, lastdiag = x-1; y <= s1len; y++) {
            olddiag = column[y];
            column[y] = MIN3(column[y] + 1, column[y-1] + 1, lastdiag + (s1[y-1] == s2[x-1] ? 0 : 1));
            lastdiag = olddiag;
        }
    }
    return(column[s1len]);
}

// dynamically allocated result need to be freed again. better to pass through parameters, which is GC-ed by python
void levenshtein_batch(char **sArr, unsigned int lenArr, char *s2, unsigned int* result) {
    unsigned int index;
    for (index = 0; index <lenArr; index++)  {
#ifdef DEBUG
        printf("%d-th/%d string (length %d): %s\n", index, lenArr, strlen(sArr[index]), sArr[index]);
#endif
        result[index] = levenshtein(sArr[index], s2);
    }
}

int main() {
    char *sArr[] = {"hello", "hello world", "hello, fine. thank you", "你好，世界"};
    char *strB = "hello world";
    int index;
    unsigned int result[4];
    printf("separate call\n");
    for (index=0; index<4; index++)
        printf("distance is %d\n", levenshtein(sArr[index], strB));
    printf("batch call\n");
    levenshtein_batch(sArr, 4, strB, result);
    for (index=0; index<4; index++)
        printf("distance is %d\n", result[index]);
    return 0;
}
