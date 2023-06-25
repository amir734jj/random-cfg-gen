using CommandLine;

namespace App.Models;

public class Options
{
    [Value(0, HelpText = "number of non-terminals", Required = true)]
    public int NonTerminals { get; set; }
    
    [Option(Required = false, HelpText = "number of characters in each terminal or non-terminal", Default = 5)]
    public int ItemLength { get; set; }
    
    [Option("DisallowEpsilon", Required = false, HelpText = "whether to disallow epsilon productions", Default = false)]
    public bool DisallowEpsilon { get; set; }
    
    [Option("DisallowAlternative", Required = false, HelpText = "whether to disallow alternative form of the production", Default = false)]
    public bool DisallowAlternative { get; set; }
}