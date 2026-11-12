#pragma once
#include <cstddef>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
namespace csv_reconcile {
// Bounded, in-memory row comparison: unlike Python, no CSV parsing, SQLite or decimal normalization.
struct Row {std::string key; std::map<std::string,std::string> fields;};
enum class Status {Matched,Changed,LeftOnly,RightOnly,Duplicate};
struct Result {std::string key;Status status;};
inline std::vector<Result> reconcile(const std::vector<Row>& left,const std::vector<Row>& right,std::size_t max_rows=10000){
 if(left.size()>max_rows||right.size()>max_rows||max_rows>100000)throw std::invalid_argument("row limit");
 using Group=std::vector<const Row*>;
 std::map<std::string,Group> a,b;
 for(const auto& r:left){if(r.key.empty()||r.key.size()>256)throw std::invalid_argument("invalid key");a[r.key].push_back(&r);}
 for(const auto& r:right){if(r.key.empty()||r.key.size()>256)throw std::invalid_argument("invalid key");b[r.key].push_back(&r);}
 std::vector<Result> out;
 for(const auto& entry:a){
  auto it=b.find(entry.first);
  if(entry.second.size()>1||(it!=b.end()&&it->second.size()>1))out.push_back({entry.first,Status::Duplicate});
  else if(it==b.end())out.push_back({entry.first,Status::LeftOnly});
  else out.push_back({entry.first,entry.second.front()->fields==it->second.front()->fields?Status::Matched:Status::Changed});
 }
 for(const auto& entry:b)if(a.find(entry.first)==a.end())
  out.push_back({entry.first,entry.second.size()>1?Status::Duplicate:Status::RightOnly});
 return out;
}
}
