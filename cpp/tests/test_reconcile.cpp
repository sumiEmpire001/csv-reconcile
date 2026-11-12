#include "reconcile.hpp"
#include <cassert>
#include <stdexcept>
int main(){
 using namespace csv_reconcile;
 std::vector<Row> a={{"01",{{"amount","0.10"}}},{"02",{{"amount","1"}}},{"02",{{"amount","2"}}},{"03",{{"amount","4"}}}};
 std::vector<Row> b={{"01",{{"amount","0.1"}}},{"02",{{"amount","1"}}},{"04",{{"amount","4"}}}};
 auto r=reconcile(a,b);assert(r.size()==4);
 assert(r[0].status==Status::Changed);assert(r[1].status==Status::Duplicate);
 assert(r[2].status==Status::LeftOnly);assert(r[3].status==Status::RightOnly);
 bool bad=false;try{reconcile({{"",{{"a","b"}}}},{});}catch(const std::invalid_argument&){bad=true;}assert(bad);
 bad=false;try{reconcile(a,b,1);}catch(const std::invalid_argument&){bad=true;}assert(bad);
}
