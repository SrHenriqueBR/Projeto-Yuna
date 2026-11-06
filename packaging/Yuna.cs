using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Windows.Forms;
using System.Reflection;

[assembly: AssemblyTitle("Yuna")]
[assembly: AssemblyDescription("Assistente pessoal Yuna")]
// AssemblyVersion/FileVersion são gerados de self_model.VERSION no build.

internal static class Program {
    [STAThread]
    private static int Main(string[] args) {
        // O processo Yuna mantém o mutex enquanto seu runtime estiver aberto.
        using (var mutex = new Mutex(false, @"Local\ProjetoYuna.App")) {
            try {
                string mode = args.Length == 0 ? "--compact" : args[0];
                if (args.Length > 1 || (mode != "--compact" && mode != "--background" &&
                    mode != "--central" && mode != "--smoke-test"))
                    throw new ArgumentException("Abra as ferramentas pela Central da Yuna.");
                string root = AppDomain.CurrentDomain.BaseDirectory;
                string python = Path.Combine(root, "runtime", "pythonw.exe");
                string script = Path.Combine(root, "app", "yuna_launcher.py");
                if (!File.Exists(python) || !File.Exists(script))
                    throw new FileNotFoundException("Arquivos do aplicativo ausentes. Execute Yuna-Setup.exe para reparar.");
                var start = new ProcessStartInfo(python, "-X utf8 \"" + script + "\" " + mode);
                start.WorkingDirectory = Path.GetDirectoryName(script);
                start.UseShellExecute = false;
                start.CreateNoWindow = true;
                start.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
                using (var child = Process.Start(start)) {
                    child.WaitForExit();
                    return child.ExitCode;
                }
            } catch (Exception error) {
                if (args.Length == 0 || args[0] != "--smoke-test")
                    MessageBox.Show(error.Message, "Yuna - inicializacao", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
    }
}
