namespace Shop { public enum Status { Open } public class Order { public static Order Make() => new Order(); } }
namespace App.Shop { public enum Status { Open } public class Order { public static Order Make() => new Order(); } }
namespace App
{
    public class A
    {
        public global::Shop.Order F1;
        public Shop.Order F2;
        public object B1() => global::Shop.Status.Open;
        public object B2() => global::Shop.Order.Make();
        public object B3() => new global::Shop.Order();
        public object B4() => Shop.Status.Open;
        public object B5() => typeof(global::Shop.Order);
    }
}
