import java.io.IOException;
import java.io.PrintWriter;
import java.lang.module.ModuleDescriptor;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileSystem;
import java.nio.file.FileSystems;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.stream.Stream;

/**
 * The members a class outside the JDK inherits by name from a JDK supertype: the nested
 * types and fields that are public or protected, the JDK's own and those it inherits.
 * `oracle.py jdk` writes skills/draftsman/scripts/draftsman/langs/java_jdk.json with it:
 *
 *   java JdkMembers.java OUT.json
 *
 * Only types a class can extend or implement (no final classes) with at least one such
 * member are listed; "supers" names the listed supertypes, whose members are inherited.
 */
public class JdkMembers {
    record Entry(List<String> supers, TreeSet<String> types, TreeSet<String> fields) {}

    public static void main(String[] args) throws IOException {
        Map<String, Class<?>> all = new TreeMap<>();
        FileSystem jrt = FileSystems.getFileSystem(URI.create("jrt:/"));
        for (Module m : ModuleLayer.boot().modules()) {
            ModuleDescriptor d = m.getDescriptor();
            for (ModuleDescriptor.Exports e : d.exports()) {
                if (e.isQualified()) {
                    continue;   // exported to named JDK modules only
                }
                Path dir = jrt.getPath("modules", d.name(), e.source().replace('.', '/'));
                if (!Files.isDirectory(dir)) {
                    continue;
                }
                try (Stream<Path> files = Files.list(dir)) {
                    for (Path f : (Iterable<Path>) files::iterator) {
                        String n = f.getFileName().toString();
                        if (!n.endsWith(".class") || n.equals("module-info.class")
                                || n.equals("package-info.class")) {
                            continue;
                        }
                        try {
                            Class<?> c = Class.forName(e.source() + "." + n.replace(".class", ""),
                                    false, ClassLoader.getPlatformClassLoader());
                            if (visible(c)) {
                                all.put(c.getCanonicalName(), c);
                            }
                        } catch (ClassNotFoundException | LinkageError ex) {
                            // a class of another platform (sun.* behind an export)
                        }
                    }
                }
            }
        }

        Map<String, Entry> own = new TreeMap<>();
        for (Class<?> c : all.values()) {
            TreeSet<String> types = new TreeSet<>();
            for (Class<?> m : c.getDeclaredClasses()) {
                if (inherited(m.getModifiers())) {
                    types.add(m.getSimpleName());
                }
            }
            TreeSet<String> fields = new TreeSet<>();
            for (Field f : c.getDeclaredFields()) {
                if (inherited(f.getModifiers()) && !f.isSynthetic()) {
                    fields.add(f.getName());
                }
            }
            List<String> supers = new ArrayList<>();
            if (c.getSuperclass() != null) {
                supers.add(c.getSuperclass().getCanonicalName());
            }
            for (Class<?> i : c.getInterfaces()) {
                supers.add(i.getCanonicalName());
            }
            own.put(c.getCanonicalName(), new Entry(supers, types, fields));
        }

        Map<String, Entry> out = new LinkedHashMap<>();
        for (Map.Entry<String, Entry> e : own.entrySet()) {
            Class<?> c = all.get(e.getKey());
            if (Modifier.isFinal(c.getModifiers()) || c.isEnum() || c.isRecord()
                    || c.isAnnotation() || !hasMembers(e.getKey(), own)) {
                continue;
            }
            List<String> supers = e.getValue().supers().stream()
                    .filter(s -> own.containsKey(s) && hasMembers(s, own)).toList();
            out.put(e.getKey(), new Entry(supers, e.getValue().types(), e.getValue().fields()));
        }

        try (PrintWriter w = new PrintWriter(Files.newBufferedWriter(Path.of(args[0]),
                StandardCharsets.UTF_8))) {
            w.println("{");
            w.println("  \"jdk\": \"" + Runtime.version() + "\",");
            w.println("  \"types\": {");
            int i = 0;
            for (Map.Entry<String, Entry> e : out.entrySet()) {
                Entry v = e.getValue();
                w.print("    \"" + e.getKey() + "\": {\"supers\": " + list(v.supers())
                        + ", \"types\": " + list(v.types()) + ", \"fields\": " + list(v.fields()) + "}");
                w.println(++i < out.size() ? "," : "");
            }
            w.println("  }");
            w.println("}");
        }
    }

    /** A public type, or a nested type a subclass outside its package sees. */
    static boolean visible(Class<?> c) {
        for (Class<?> t = c; t != null; t = t.getDeclaringClass()) {
            if (!inherited(t.getModifiers()) || t.isAnonymousClass() || t.isLocalClass()) {
                return false;
            }
        }
        return c.getCanonicalName() != null;
    }

    static boolean inherited(int mod) {
        return Modifier.isPublic(mod) || Modifier.isProtected(mod);
    }

    static boolean hasMembers(String name, Map<String, Entry> own) {
        Entry e = own.get(name);
        if (e == null) {
            return false;
        }
        if (!e.types().isEmpty() || !e.fields().isEmpty()) {
            return true;
        }
        for (String s : e.supers()) {
            if (hasMembers(s, own)) {
                return true;
            }
        }
        return false;
    }

    static String list(Iterable<String> xs) {
        StringBuilder b = new StringBuilder("[");
        for (String x : xs) {
            b.append(b.length() > 1 ? ", " : "").append('"').append(x).append('"');
        }
        return b.append(']').toString();
    }
}
