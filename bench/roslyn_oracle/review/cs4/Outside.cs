using Microsoft.AspNetCore.Mvc;
using Shop;
namespace App.Controllers
{
    // ControllerBase.User and .Request, Exception.Data: members of outside base classes
    public class UsersController : ControllerBase
    {
        public object A() => User.Identity;
        public object B() => Request.Path;
        public object C() => new User();
        public object D() => nameof(User);
    }
    public class ShopException : System.Exception
    {
        public object A() => Data.Count;
    }
}
