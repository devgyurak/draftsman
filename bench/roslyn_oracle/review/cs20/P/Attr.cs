namespace Shop
{
    public class Holder
    {
        public Kind Kind;

        [Tag(Kind.A)]
        public void M() { }

        [Tag(nameof(Kind))]
        public void N() { }

        public class In
        {
            [Tag(Kind.B)]
            public void P() { }
        }
    }

    public class Str
    {
        public string Cash = "";

        [Tag(nameof(Cash))]
        public void M() { }

        public Cash C2;
        public Cash Get(Cash c) => c;
    }
}
