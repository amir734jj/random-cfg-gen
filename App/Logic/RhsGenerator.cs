using App.Models;

namespace App.Logic;

public class RhsGenerator
{
    private readonly RandomGen _randomGen;
    private readonly State _state;
    private readonly ItemGenerator _itemGenerator;
    private readonly Utilities _utilities;
    private readonly Options _options;

    public RhsGenerator(RandomGen randomGen, State state, ItemGenerator itemGenerator, Utilities utilities, Options options)
    {
        _randomGen = randomGen;
        _state = state;
        _itemGenerator = itemGenerator;
        _utilities = utilities;
        _options = options;
    }

    public string Invoke(string nt)
    {
        var rhsCount = _randomGen.Rand(
            _options.DisallowEpsilon || _state.EpsilonGenerated[nt]
                ? _utilities.WithoutEpsilonRhs(_state.rhsDistribution)
                : _state.rhsDistribution);

        if (rhsCount == 0)
        {
            _state.EpsilonGenerated[nt] = true;
        }

        return string.Join(" ", Enumerable.Range(0, rhsCount)
            .Select(x => _itemGenerator.Invoke()));
    }
}