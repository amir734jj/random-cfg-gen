using App.Models;

namespace App.Logic;

public class CfgGenerator
{
    private readonly State _state;
    private readonly ProductionGenerator _productionGenerator;

    public CfgGenerator(State state, ProductionGenerator productionGenerator)
    {
        _state = state;
        _productionGenerator = productionGenerator;
    }
    
    public string Invoke()
    {
        return string.Join("", _state.NonTerminals
            .SelectMany(nt => _productionGenerator.Invoke(nt).Select(p => $"{nt} ::= {p} ;\n")));
    }
}