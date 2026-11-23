using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using Microsoft.AspNetCore.Mvc;
using Shop;
using Base = Microsoft.AspNetCore.Mvc.ControllerBase;
namespace App.B
{
    public class Basket : Collection<int>
    {
        public object A() => Items.Count;
        public object B() => User.Count;
    }
    public class Orders : List<int>
    {
        public object A() { Enumerator e = GetEnumerator(); return e; }
        public object B() => typeof(Enumerator);
    }
    public class Mid : ControllerBase { }
    public class Leaf : Mid
    {
        public object A() => User.Identity;
        public object B() => Request.Path;
        public object C() => Order.Count;
    }
    public partial class Part
    {
        public object A() => User.Identity;
        public object B() => nameof(Request);
    }
    public class Aliased : Base { public object A() => User.Identity; }
    public class Qualified : Microsoft.AspNetCore.Mvc.ControllerBase { public object A() => User.Identity; }
    public class Io : IOException { public object A() => Data.Count; }
    public class Outer : ControllerBase
    {
        public class Inner
        {
            public object A() => nameof(User);
            public object B() => nameof(Order);
        }
    }
    public class FieldInit : ControllerBase
    {
        public object F = nameof(User);
        public static object G = nameof(Request);
    }
}
