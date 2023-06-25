namespace App;

class Program
{
    private static readonly Random Random = new();

    public static string RandomLowerCaseString(int length)
    {
        const string chars = "abcdefghijklmnopqrstuvwxyz";
        return new string(Enumerable.Repeat(chars, length)
            .Select(s => s[Random.Next(s.Length)]).ToArray());
    }

    public static string RandomUpperCaseString(int length)
    {
        const string chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        return new string(Enumerable.Repeat(chars, length)
            .Select(s => s[Random.Next(s.Length)]).ToArray());
    }

    public static (int Height, int Width) GetDimension(int p)
    {
        int a = 2;
        int b = 4;
        return ((int)(Math.Pow(a, p - 1) * b), (int)Math.Pow(a, p));
    }

    public static void Main(string[] args)
    {
        int[] heights = Enumerable.Range(1, 5).ToArray();

        foreach (var p in heights)
        {
            var (height, width) = GetDimension(p);

            var nonTerminals = Enumerable.Range(0, height)
                .Select(x => RandomUpperCaseString(5))
                .ToList();

            var path = $"/home/hesamian/workspace/random-grammars/grammar{height}.cfg";
            File.Delete(path);
            var terminals = new Dictionary<string, bool>();

            using var f = new FileStream(path, FileMode.OpenOrCreate, FileAccess.ReadWrite);
            {
                using var s = new StreamWriter(f);

                foreach (var nonTerminal in nonTerminals)
                {
                    s.Write(nonTerminal + " ::= ");
                    var cntRhsTerminals = 0;
                    for (var j = 0; j < width; j++)
                    {
                        var value = Random.Next(100);
                        var result = value <= 50;

                        if (result || cntRhsTerminals >= Math.Ceiling(nonTerminals.Count / 2.0))
                        {
                            var terminal = RandomLowerCaseString(5);
                            
                            s.Write($"\"{terminal}\" ");

                            terminals.TryAdd(terminal, true);
                        }
                        else
                        {
                            s.Write($"{nonTerminals[Random.Next(nonTerminals.Count)]} ");
                            cntRhsTerminals++;
                        }
                    }

                    s.WriteLine(";");
                }

                s.WriteLine("\n");
                s.WriteLine("\n");
            }
            
            /*
            Console.WriteLine($"nodes: {nonTerminals.Count + terminals.Count} non-terminals: {nonTerminals.Count} terminals: {terminals.Count}");
            File.Copy(path, "/home/hesamian/workspace/crag-artifact/TestGrammars/grammar.cfg", true);
            
            var cliProcess = new Process
            {
                StartInfo = new ProcessStartInfo("java", "-Xmx8g -cp .:tools/junit.jar testframework.TestAll -text TestFollow.class") {
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    WorkingDirectory = "/home/hesamian/workspace/crag-artifact",
                }
            };
            cliProcess.Start();
            var cliOut = cliProcess.StandardOutput.ReadToEnd();
            Console.WriteLine(cliOut);
            cliProcess.WaitForExit();
            cliProcess.Close();

            GC.Collect();
            Console.ReadKey(); */
        }
    }
}