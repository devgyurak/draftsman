using Shop;
namespace CommunityToolkit.Mvvm.Input.Mine
{
    // the namespace around is a package's: its RelayCommand comes before the file's using
    public class InPackage
    {
        public object A() => typeof(RelayCommand);
        public object B() => Order.Count;
    }
}
namespace CommunityToolkit.Mvvm.ComponentModel
{
    using Shop;
    public class Same
    {
        public object A() => typeof(ObservableObject);
        public object B() => Order.Count;
    }
}
