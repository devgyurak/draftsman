namespace Shop
{
    public class RelayCommand { public static int Count = 0; }
    public class ObservableObject { public static int Count = 0; }
    public class Order { public static int Count = 0; }
    public class Host { public static int Count = 0; }
    public class Lib { public class Order { public static int Count = 0; } }
}
namespace Lib { public class Order { public static int Count = 1; } }
namespace Models { public class Order { public static int Count = 2; } }
namespace App.Models { public class Order { public static int Count = 3; } }
