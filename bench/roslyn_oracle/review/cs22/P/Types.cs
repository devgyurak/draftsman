namespace Lib { public class Order {} public class Item {} }
namespace Lib.Sub { public class Order {} public class Item {} }
// rivals: Shop.Order, Shop.Lib.Order, a namespace Shop.Lib.Sub, a class L
namespace Shop { public class Order {} public class L { public class Order {} } }
namespace Shop.Lib { public class Order {} }
namespace Shop.Lib.Sub { public class Item {} }
