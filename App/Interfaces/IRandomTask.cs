namespace App.Interfaces;

internal interface IRandomTask<out TResult>
{
    public TResult Invoke();
}