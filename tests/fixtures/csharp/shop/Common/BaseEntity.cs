using System;

namespace Shop.Common
{
    public interface IAuditable
    {
        DateTime CreatedAt { get; }
    }

    public abstract class BaseEntity : IAuditable
    {
        protected long Id;
        public DateTime CreatedAt { get; private set; }
        public abstract bool IsNew();

        public interface IListener
        {
            void Changed(BaseEntity entity);
        }
    }
}
