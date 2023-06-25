using App.Models;

namespace App.Logic;

public class ProductionGenerator
{
    private readonly RandomGen _randomGen;
    private readonly State _state;
    private readonly RhsGenerator _rhsGenerator;
    private readonly Options _options;

    public ProductionGenerator(RandomGen randomGen, State state, RhsGenerator rhsGenerator, Options options)
    {
        _randomGen = randomGen;
        _state = state;
        _rhsGenerator = rhsGenerator;
        _options = options;
    }
    
    public List<string> Invoke(string nt)
    {
        return Enumerable.Range(0, !_options.DisallowAlternative ? _randomGen.Rand(_state.productionsDistribution) : 1)
            .Select(x => _rhsGenerator.Invoke(nt))
            .ToList();
    }
}