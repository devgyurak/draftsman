namespace Shop.Dead3
{
    public class Branches
    {
#if false
        public object A1() => Order.Count;
#elif true
        public object A2() => Order.Count;
#else
        public object A3() => Order.Count;
#endif
#if true
        public object B1() => Order.Count;
#elif DEBUG
        public object B2() => Order.Count;
#else
        public object B3() => Order.Count;
#endif
#if DEBUG
        public object C1() => Order.Count;
#elif true
        public object C2() => Order.Count;
#endif
#if !false
        public object D1() => Order.Count;
#else
        public object D2() => Order.Count;
#endif
#if false
#if true
        public object E1() => Order.Count;
#else
        public object E2() => Order.Count;
#endif
#else
#if false
        public object E3() => Order.Count;
#else
        public object E4() => Order.Count;
#endif
#endif
#if true && false
        public object F1() => Order.Count;
#else
        public object F2() => Order.Count;
#endif
#if DEBUG && false
        public object G1() => Order.Count;
#else
        public object G2() => Order.Count;
#endif
#if DEBUG || true
        public object H1() => Order.Count;
#else
        public object H2() => Order.Count;
#endif
#if false == false
        public object I1() => Order.Count;
#else
        public object I2() => Order.Count;
#endif
#if true != true
        public object J1() => Order.Count;
#else
        public object J2() => Order.Count;
#endif
#if false // switched off
        public object K1() => Order.Count;
#else // on
        public object K2() => Order.Count;
#endif
        #  if !(true)
        public object L1() => Order.Count;
        #  else
        public object L2() => Order.Count;
        #  endif
#if false
        public int Money = 0;
#elif true
        public int Other = 0;
#else
        public int Order = 0;
#endif
        public object M() => Money.Count;
    }
#if false
    public class Dup { public static int Count; }
#else
    public class Dup { public static int Count; }
#endif
    public class UseDup { public object A() => Dup.Count; }
}
