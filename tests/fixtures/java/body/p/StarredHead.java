package p;

import java.awt.geom.*;

// a head no import of the sources resolves is no package when it is a type of the default
// package: a named package cannot see those
class StarredHead {
    int wind() {
        return Path2D.Double.WIND_EVEN_ODD;                 //> Path2D=java.awt.geom.Path2D/r Double=java.awt.geom.Path2D.Double/r
    }
}
