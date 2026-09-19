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

    [Option("rhs-continue-percent", Required = false, HelpText = "chance to add another symbol to a right-hand side", Default = 60)]
    public int RhsContinuationPercent { get; set; }

    [Option("alternative-continue-percent", Required = false, HelpText = "chance to add another alternative to a production", Default = 60)]
    public int AlternativeContinuationPercent { get; set; }

    [Option("epsilon-percent", Required = false, HelpText = "chance that an eligible alternative is epsilon", Default = 10)]
    public int EpsilonPercent { get; set; }

    [Option("seed", Required = false, HelpText = "random seed for reproducible generation")]
    public int? Seed { get; set; }
}