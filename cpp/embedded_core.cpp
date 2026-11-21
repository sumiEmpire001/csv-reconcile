#include <stdint.h>
#include <stddef.h>
#include <string.h>
namespace embedded_reconcile {
enum Status { OK, INVALID, CAPACITY, DUPLICATE, MISSING, DIFFERENT, MATCHED };
template<size_t ROWS,size_t KEY_BYTES,size_t VALUE_BYTES> class Reconciler {
 struct Row {char key[KEY_BYTES];char value[VALUE_BYTES];};
 Row left_[ROWS],right_[ROWS];size_t nl_,nr_;bool fault_;
 static bool valid(const char* s,size_t max){if(!s||!s[0])return false;for(size_t i=0;i<max;++i){if(!s[i])return true;if((unsigned char)s[i]<32)return false;}return false;}
 Status insert(Row* rows,size_t &n,const char* key,const char* value){
  if(fault_)return INVALID;
  if(!valid(key,KEY_BYTES)||!valid(value,VALUE_BYTES)){fault_=true;return INVALID;}
  if(n==ROWS){fault_=true;return CAPACITY;}
  for(size_t i=0;i<n;++i)if(strcmp(rows[i].key,key)==0){fault_=true;return DUPLICATE;}
  strcpy(rows[n].key,key);strcpy(rows[n].value,value);++n;return OK;
 }
public:
 Reconciler():nl_(0),nr_(0),fault_(false){}
 Status add_left(const char*k,const char*v){return insert(left_,nl_,k,v);}
 Status add_right(const char*k,const char*v){return insert(right_,nr_,k,v);}
 Status compare(const char*k)const{
  if(fault_||!valid(k,KEY_BYTES))return INVALID;
  const char *a=0,*b=0;
  for(size_t i=0;i<nl_;++i)if(strcmp(left_[i].key,k)==0)a=left_[i].value;
  for(size_t i=0;i<nr_;++i)if(strcmp(right_[i].key,k)==0)b=right_[i].value;
  if(!a||!b)return MISSING;
  return strcmp(a,b)==0?MATCHED:DIFFERENT;
 }
 bool faulted()const{return fault_;}
 void reset(){nl_=nr_=0;fault_=false;}
};
}
#ifdef EMBEDDED_TEST
#include <assert.h>
int main(){using namespace embedded_reconcile;Reconciler<2,8,16> r;assert(r.add_left("A","12")==OK);assert(r.add_right("A","12")==OK);assert(r.compare("A")==MATCHED);assert(r.add_right("B","13")==OK);assert(r.compare("B")==MISSING);assert(r.add_left("A","14")==DUPLICATE);assert(r.faulted());r.reset();assert(r.add_left("A","0.10")==OK);assert(r.add_right("A","0.1")==OK);assert(r.compare("A")==DIFFERENT);assert(r.add_left("12345678","x")==INVALID);return 0;}
#endif
