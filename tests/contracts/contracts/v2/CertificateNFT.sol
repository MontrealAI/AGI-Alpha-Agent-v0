// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./Constants.sol";

/// @title CertificateNFT
/// @notice ERC721 token representing job completion certificates with optional
/// marketplace functionality where payments are strictly in $AGIALPHA.
contract CertificateNFT is ERC721, Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    IERC20 public agiAlpha;
    address public jobRegistry;
    string private baseTokenURI;

    struct Listing {
        address seller;
        uint256 price;
    }

    mapping(uint256 => Listing) public listings;

    event NFTIssued(address indexed to, uint256 indexed tokenId, uint256 indexed jobId);
    event NFTListed(uint256 indexed tokenId, address indexed seller, uint256 price);
    event NFTPurchased(uint256 indexed tokenId, address indexed buyer, uint256 price);
    event NFTDelisted(uint256 indexed tokenId);

    constructor(address _agiToken) ERC721("CertificateNFT", "CERT") Ownable(msg.sender) {
        agiAlpha = IERC20(_agiToken);
        require(
            IERC20Metadata(_agiToken).decimals() == Constants.AGIALPHA_DECIMALS,
            "wrong decimals"
        );
    }

    /// @notice Sets the JobRegistry authorized to mint certificates
    function setJobRegistry(address registry) external onlyOwner {
        jobRegistry = registry;
    }

    /// @notice Updates the base URI for token metadata
    function setBaseURI(string memory uri) external onlyOwner {
        baseTokenURI = uri;
    }

    /// @dev Returns the base URI for token metadata
    function _baseURI() internal view override returns (string memory) {
        return baseTokenURI;
    }

    /// @notice Mints a certificate NFT for a completed job
    function mint(address to, uint256 jobId) external {
        require(msg.sender == jobRegistry, "not registry");
        _safeMint(to, jobId);
        emit NFTIssued(to, jobId, jobId);
    }

    /// @notice Lists a certificate NFT for sale
    function list(uint256 tokenId, uint256 price) external nonReentrant {
        require(ownerOf(tokenId) == msg.sender, "not owner");
        require(price > 0, "price 0");
        listings[tokenId] = Listing({seller: msg.sender, price: price});
        emit NFTListed(tokenId, msg.sender, price);
    }

    /// @notice Removes a certificate NFT from sale
    function delist(uint256 tokenId) external nonReentrant {
        Listing memory listing = listings[tokenId];
        require(listing.seller == msg.sender, "not seller");
        delete listings[tokenId];
        emit NFTDelisted(tokenId);
    }

    /// @notice Purchases a listed certificate NFT using $AGIALPHA tokens
    /// Only $AGIALPHA is accepted for marketplace payments
    function purchase(uint256 tokenId) external nonReentrant {
        Listing memory listing = listings[tokenId];
        require(listing.price > 0, "not listed");
        require(ownerOf(tokenId) == listing.seller, "not seller");
        delete listings[tokenId];
        _transfer(listing.seller, msg.sender, tokenId);
        agiAlpha.safeTransferFrom(msg.sender, listing.seller, listing.price);
        emit NFTPurchased(tokenId, msg.sender, listing.price);
    }
}

