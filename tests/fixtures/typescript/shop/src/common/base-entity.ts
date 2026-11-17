export interface Auditable {
  readonly createdAt: Date;
}

export abstract class BaseEntity implements Auditable {
  protected id?: number;
  readonly createdAt: Date = new Date();
  abstract isNew(): boolean;
}

export namespace BaseEntity {
  export interface Listener {
    changed(entity: BaseEntity): void;
  }
}
