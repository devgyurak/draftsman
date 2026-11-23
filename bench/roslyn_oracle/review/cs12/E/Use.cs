using CommunityToolkit.Mvvm.Extras.Models;
namespace CommunityToolkit.Mvvm.Extras.Views
{
    public class View
    {
        public object A() => new Item();
        public object B() => Item.Count;
        public object C() => Helper.Count;
        public object D() => new CommunityToolkit.Mvvm.Extras.Models.Box();
        public object E() => new Models.Box();
        public object F() => new View();
    }
}
