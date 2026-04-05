using System.Threading.Tasks;

namespace CodeGuardian.Tests.Fixtures
{
    public class UserService
    {
        private readonly IUserRepository _userRepository;
        private readonly IEmailService _emailService;

        public UserService(IUserRepository userRepository, IEmailService emailService)
        {
            _userRepository = userRepository;
            _emailService = emailService;
        }

        public async Task<Result<UserDto>> GetUserAsync(int userId)
        {
            var user = await _userRepository.FindByIdAsync(userId);
            if (user == null)
                return Result<UserDto>.Failure("Usuario nao encontrado");

            return Result<UserDto>.Success(new UserDto(user.Id, user.Name, user.Email));
        }

        public async Task<Result<bool>> UpdateEmailAsync(int userId, string newEmail)
        {
            if (string.IsNullOrWhiteSpace(newEmail))
                return Result<bool>.Failure("Email invalido");

            var updated = await _userRepository.UpdateEmailAsync(userId, newEmail);
            return Result<bool>.Success(updated);
        }
    }
}
