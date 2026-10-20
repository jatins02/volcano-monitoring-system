import com.cburch.logisim.comp.ComponentDrawContext;
import com.cburch.logisim.file.Loader;
import com.cburch.logisim.proj.Project;
import java.awt.Color;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import javax.xml.parsers.DocumentBuilderFactory;

/** Developer QA using the pinned Logisim loader and native component painters.
 * Arguments: project.circ circuit-name output.png [scale]. This renders an
 * artifact; it never controls a desktop window or substitutes monitor outputs.
 */
public final class RenderCircuit {
  public static void main(String[] args) {
    try {
      render(args);
      System.exit(0);
    } catch (Exception error) {
      error.printStackTrace();
      System.exit(1);
    }
  }

  private static void render(String[] args) throws Exception {
    if (args.length < 3 || args.length > 4) {
      throw new IllegalArgumentException("Expected: project.circ circuit-name output.png [scale]");
    }
    com.cburch.logisim.Main.headless = true;
    var xmlFactory = DocumentBuilderFactory.newInstance();
    xmlFactory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    var xml = xmlFactory.newDocumentBuilder().parse(new File(args[0]));
    var loaded = new Loader(null).openLogisimFile(new File(args[0]));
    var circuits = xml.getElementsByTagName("circuit");
    int total = 0;
    for (int i = 0; i < circuits.getLength(); i++) {
      var node = (org.w3c.dom.Element) circuits.item(i);
      var name = node.getAttribute("name");
      int expected = node.getElementsByTagName("comp").getLength();
      int actual = loaded.getCircuit(name).getNonWires().size();
      if (actual != expected) {
        throw new IllegalStateException(name + ": Logisim loaded " + actual + " of " + expected + " components");
      }
      total += actual;
    }
    System.out.println("Native loader preserved all " + total + " components in " + circuits.getLength() + " circuits");
    var circuit = loaded.getCircuit(args[1]);
    if (circuit == null) throw new IllegalArgumentException("Unknown circuit: " + args[1]);
    var project = new Project(loaded);
    try {
      var state = project.getCircuitState(circuit);
      var scratch = new BufferedImage(1, 1, BufferedImage.TYPE_INT_RGB).createGraphics();
      var bounds = circuit.getBounds(scratch).expand(30);
      scratch.dispose();
      System.out.println(circuit.getName() + " bounds=" + bounds);
      double scale = args.length > 3 ? Double.parseDouble(args[3]) : 1;
      if (!Double.isFinite(scale) || scale <= 0 || scale > 4) {
        throw new IllegalArgumentException("Scale must be greater than zero and at most four");
      }
      var image = new BufferedImage((int)(bounds.getWidth()*scale), (int)(bounds.getHeight()*scale), BufferedImage.TYPE_INT_RGB);
      var graphics = image.createGraphics();
      try {
        graphics.setColor(Color.WHITE);
        graphics.fillRect(0, 0, image.getWidth(), image.getHeight());
        graphics.setColor(Color.BLACK);
        graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        graphics.scale(scale, scale);
        graphics.translate(-bounds.getX(), -bounds.getY());
        // Printer view checks the actual native symbols and layout. Numerical
        // simulation behavior is verified separately by the CLI fixture suites.
        circuit.draw(new ComponentDrawContext(null, circuit, state, graphics, graphics, true), null);
      } finally {
        graphics.dispose();
      }
      if (!ImageIO.write(image, "png", new File(args[2]))) {
        throw new IllegalStateException("PNG writer unavailable");
      }
    } finally {
      project.getSimulator().shutDown();
    }
  }
}
