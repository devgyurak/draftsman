import { Foo } from "./foo";
import { Shop } from "./shop";

function Panel(props: { children?: unknown }): unknown {
  return props.children;
}

export class Widget {
  render(): unknown {
    return <Panel><Foo /><Shop.Item /></Panel>;    //> Panel=var/r Panel=- Foo=p/foo.Foo/r Shop=- Item=p/shop.Shop.Item/r
  }
}
