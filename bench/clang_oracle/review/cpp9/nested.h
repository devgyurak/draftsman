#pragma once
// a class's own nested type it only declares, defined where the header is included
namespace own {
class Table {
 public:
  struct Rep;
  Rep* rep_;
  Table(Rep* r);
};
}
