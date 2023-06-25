namespace App.Interfaces;

public interface IRandomTask<out TResult>
{
    public TResult Invoke();
}