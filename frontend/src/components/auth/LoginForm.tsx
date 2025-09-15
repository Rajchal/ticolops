import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { useAuth } from '../../contexts/AuthContext';

export const LoginForm: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-400">
      {/* Big flex box with yellow gradient */}
      <div className="w-11/12 lg:w-3/4 xl:w-2/3 
             bg-gradient-to-b from-indigo-100 via-blue-200 to-blue-100


                shadow-2xl rounded-3xl flex overflow-hidden">


        {/* Left: Login section (thinner) */}
        <div className="w-full lg:w-2/5 flex flex-col p-8">
        <div className="flex  mb-12">
  <header className="inline-block p-2 rounded-3xl shadow-sm border border-gray-400">
    <h1 className="text-sm text-gray-900 inline-block">
      Ticolops
    </h1>
  </header>

  
</div>




          <div className="flex-1 flex items-center justify-center">
            <div className="w-full max-w-md">
              {/* Headings */}
              <div className="text-center mb-6">
                <h2 className="text-3xl text-gray-900">
                  Sign in to your account
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                  Track. Collaborate. Deploy. Succeed.
                </p>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <div className="bg-red-100 text-red-600 px-4 py-3 rounded">
                    {error}
                  </div>
                )}
<Input
  label="Email address"
  type="email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  required
  placeholder="Enter your email"
  className="bg-white rounded-3xl  placeholder-gray-400 border-none focus:ring-0 shadow-sm"
  labelClassName="text-gray-500 text-sm"
/>

<Input
  label="Password"
  type="password"
  value={password}
  onChange={(e) => setPassword(e.target.value)}
  required
  placeholder="Enter your password"
  className="bg-white rounded-3xl  placeholder-gray-400 border-none focus:ring-0 shadow-sm"
  labelClassName="text-gray-500 text-sm"
/>



<Button
  type="submit"
  className="w-full bg-blue-300 hover:bg-blue-400 text-black font-medium rounded-3xl shadow-sm"
  disabled={loading}
>
  {loading ? 'Signing in...' : 'Sign in'}
</Button>


                <div className="text-center">
                  <span className="text-sm text-gray-600">
                    Don&apos;t have an account?{' '}
                    <Link
                      to="/register"
                      className="font-medium text-primary hover:text-primary/80"
                    >
                      Sign up
                    </Link>
                  </span>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* Right: Image section (larger) */}
        <div className="hidden lg:flex w-3/5 bg-gray-200">
          <img
            src="/login9.jpg"
            alt="Login illustration"
            className="h-full w-full object-cover border "
          />
        </div>
      </div>
    </div>
  );
};
