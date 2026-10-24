import com.cburch.logisim.data.Direction;
import com.cburch.logisim.file.Loader;
import java.io.File;
import javax.xml.parsers.DocumentBuilderFactory;

/** Native import gate for classic Logisim and Logisim-evolution.
 * Compile separately against each tested JAR. Loader diagnostics are failures,
 * not dialogs to dismiss; verify every component and custom port survived.
 */
public final class CheckCircuitImport {
  private static final class StrictLoader extends Loader {
    StrictLoader() { super(null); }
    @Override public void showError(String message) {
      throw new IllegalStateException(message);
    }
  }

  public static void main(String[] args) {
    try { check(args); System.exit(0); }
    catch (Exception error) { error.printStackTrace(); System.exit(1); }
  }

  private static void check(String[] args) throws Exception {
    if (args.length != 1) throw new IllegalArgumentException("Expected project.circ");
    System.setProperty("java.awt.headless", "true");
    try {
      // Evolution has a separate headless guard; classic does not expose it.
      Class.forName("com.cburch.logisim.Main").getField("headless").setBoolean(null, true);
    } catch (NoSuchFieldException classic) { }
    var xmlFactory = DocumentBuilderFactory.newInstance();
    xmlFactory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    var xml = xmlFactory.newDocumentBuilder().parse(new File(args[0]));
    var loaded = new StrictLoader().openLogisimFile(new File(args[0]));
    var circuits = xml.getElementsByTagName("circuit");
    int totalComponents = 0, totalPorts = 0;
    for (int i = 0; i < circuits.getLength(); i++) {
      var saved = (org.w3c.dom.Element) circuits.item(i);
      String name = saved.getAttribute("name");
      var circuit = loaded.getCircuit(name);
      int expected = saved.getElementsByTagName("comp").getLength();
      if (circuit == null || circuit.getNonWires().size() != expected) {
        throw new IllegalStateException(name + ": component import differs from saved XML");
      }
      totalComponents += expected;
      var savedPorts = saved.getElementsByTagName("circ-port");
      if (saved.getElementsByTagName("appear").getLength() == 0) continue;
      var ports = circuit.getAppearance().getPortOffsets(Direction.EAST);
      if (savedPorts.getLength() != ports.size()) {
        throw new IllegalStateException(name + ": custom port count changed on import");
      }
      if (savedPorts.getLength() == 0) continue;
      var anchor = (org.w3c.dom.Element) saved.getElementsByTagName("circ-anchor").item(0);
      int ax = Integer.parseInt(anchor.getAttribute("x")) + 3;
      int ay = Integer.parseInt(anchor.getAttribute("y")) + 3;
      for (int j = 0; j < savedPorts.getLength(); j++) {
        var port = (org.w3c.dom.Element) savedPorts.item(j);
        int x = Integer.parseInt(port.getAttribute("x")) + 4 - ax;
        int y = Integer.parseInt(port.getAttribute("y")) + 4 - ay;
        boolean matched = false;
        for (var entry : ports.entrySet()) {
          if (entry.getKey().getX() == x && entry.getKey().getY() == y) {
            String location = entry.getValue().getLocation().toString()
                .replace("(", "").replace(")", "").replace(" ", "");
            matched = location.equals(port.getAttribute("pin"));
          }
        }
        if (!matched) throw new IllegalStateException(name + ": port location/binding changed on import");
        totalPorts++;
      }
    }
    System.out.println("Native import: " + totalComponents + " components and " + totalPorts
        + " custom ports preserved in " + circuits.getLength() + " circuits; no loader errors");
  }
}
