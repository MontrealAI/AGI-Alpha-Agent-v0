#include <array>
#include <cstdint>
#include <iostream>
int main() {
  std::array<bool,29> s{}, next{};
  unsigned events, rst;
  while (std::cin >> events >> rst) {
    if (events > 255 || rst > 1) return 2;
    if (rst) s.fill(false);
    else {
      next[0] = !(events & 8u) && (((events & 1u)));
      next[1] = !(events & 8u) && ((s[0]));
      next[2] = !(events & 8u) && ((s[1]));
      next[3] = !(events & 8u) && ((s[0] && (events & 2u)));
      next[4] = !(events & 8u) && ((s[3]));
      next[5] = !(events & 8u) && ((s[1] && (events & 2u)));
      next[6] = !(events & 8u) && ((s[5]));
      next[7] = !(events & 8u) && ((s[2] && (events & 2u)));
      next[8] = !(events & 8u) && ((s[7]));
      next[9] = !(events & 8u) && ((s[3] && (events & 4u)));
      next[10] = !(events & 8u) && ((s[9]) || (s[4] && (events & 4u)) || (s[5] && (events & 4u)));
      next[11] = !(events & 8u) && ((s[10]) || (s[6] && (events & 4u)) || (s[7] && (events & 4u)));
      next[12] = !(events & 8u) && ((s[11]) || (s[8] && (events & 4u)));
      next[13] = !(events & 8u) && ((s[12]));
      next[14] = !(events & 8u) && ((s[13]));
      next[15] = !(events & 128u) && (((events & 16u)));
      next[16] = !(events & 128u) && ((s[15]));
      next[17] = !(events & 128u) && ((s[15] && (events & 32u)));
      next[18] = !(events & 128u) && ((s[17]));
      next[19] = !(events & 128u) && ((s[18]));
      next[20] = !(events & 128u) && ((s[16] && (events & 32u)));
      next[21] = !(events & 128u) && ((s[20]));
      next[22] = !(events & 128u) && ((s[21]));
      next[23] = !(events & 128u) && ((s[18] && (events & 64u)));
      next[24] = !(events & 128u) && ((s[23]) || (s[19] && (events & 64u)) || (s[21] && (events & 64u)));
      next[25] = !(events & 128u) && ((s[24]) || (s[22] && (events & 64u)));
      next[26] = !(events & 128u) && ((s[25]));
      next[27] = !(events & 128u) && ((s[26]));
      next[28] = !(events & 128u) && ((s[27]));
      s = next;
    }
    unsigned out = 0;
    out |= static_cast<unsigned>(s[14]) << 0;
    out |= static_cast<unsigned>(s[28]) << 1;
    std::cout << out << '\n';
  }
}
