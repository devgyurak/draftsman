namespace One { using Lib; public class X { public object A() => new Order(); public object B() => Order.Count; } }
namespace Two { using Lib2; public class Y { public object A() => new Order(); public object B() => Order.Count; } }
