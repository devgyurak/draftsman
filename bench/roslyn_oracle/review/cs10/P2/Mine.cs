namespace CommunityToolkit.Mvvm.ComponentModel.Mine
{
    public class ViaGlobal
    {
        public object A() => typeof(ObservableObject);
        public object B() => Order.Count;
    }
}
namespace System.Mine6
{
    public class GlobalOutside
    {
        public object A() => new Random();
        public object B() => Order.Count;
    }
}
namespace CommunityToolkit.Mvvm.Input.Mine2
{
    public class NoUsing
    {
        public object A() => typeof(RelayCommand);
        public object B() => typeof(CommunityToolkit.Mvvm.Input.RelayCommand);
    }
}
