export namespace Shop {
  export class Cart {
    add(): Item {
      return new Item();                      //> Item=p/shop.Shop.Item/r
    }
  }
  export class Item {}
}
