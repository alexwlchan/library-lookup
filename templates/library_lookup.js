function getAvailabilityMessage(availability) {
  if (availability.locallyAvailableCopies === 1) {
    return '1 copy nearby';
  } else if (availability.locallyAvailableCopies > 0) {
    return `${availability.locallyAvailableCopies} copies nearby`;
  }


  if (availability.availableCopies === 0) {
    return 'No copies';
  } else if (availability.availableCopies === 1 && availability.locallyAvailableCopies === 0) {
    return `${availability.availableCopies} copy`;
  } else if (availability.locallyAvailableCopies === 0) {
    return `${availability.availableCopies} copies`;
  } else if (availability.availableCopies === 1 && availability.locallyAvailableCopies === 1) {
    return '1 copy, nearby';
  } else {
    return `${availability.availableCopies} copies, ${availability.locallyAvailableCopies} nearby`;
  };
}

function getListOfCopies(availability) {
  const talliedAvailability = availability
    .map(av => `${av.location} / ${av.collection}`)
    .reduce((tally, av) => {
        tally[av] = (tally[av] || 0) + 1;
        return tally;
    }, {});

  const labels = Object.entries(talliedAvailability)
    .map(entry => {
      const [label, count] = entry;
      return count > 1 ? `${label} (&times;&thinsp;${count})` : label;
    });

  return '<ul>' + labels.map(lab => `<li>${lab}</li>`).join('') + '</ul>';
}

function getAvailabilityInfo(availability) {
  if (
    availability.locallyAvailableCopies === 0 &&
    availability.availableCopies === 0) {
    return '<p>No copies available.</p>'
  } else if (
    availability.locallyAvailableCopies === 1
  ) {
    return '<p><strong>1 copy available nearby.</strong></p>' + getListOfCopies(availability.locallyAvailableLocations);
  } else if (
    availability.locallyAvailableCopies > 1
  ) {
    return `<p><strong>${availability.locallyAvailableCopies} copies available nearby.</strong></p>` + getListOfCopies(availability.locallyAvailableLocations);
  } else if (availability.availableCopies === 1) {
    return `<p>1 copy available in ${availability.availableLocations[0].location}.</p>`
  } else {
    return `<p>${availability.availableCopies} copies available in ${availability.availableLocations.map(av => av.location).join(", ")}.</p>`
  }

  return `<p><strong>Availability:</strong></p> ${JSON.stringify(availability)}`;
}

function renderBooks() {
  const selectedBranches =
    Array.from(document.querySelectorAll('#branch_picker input'))
      .filter(input => input.checked)
      .map(input => input.value);

  // Build a tally { bookId => how many available copies }
  const bookAvailability = Object.fromEntries(
    books
      .map(function(book) {
        const availableLocations = book.availability_info
          .filter(av => av.status === 'Available');

        const locallyAvailableLocations = availableLocations
          .filter(av => selectedBranches.includes(av.location));

        const locallyAvailableCopies = locallyAvailableLocations.length;

        const availableCopies = book.availability_info
          .filter(av => av.status === 'Available')
          .length;

        return [book.id, { locallyAvailableCopies, locallyAvailableLocations, availableLocations, availableCopies } ];
      })
  );

  // Go through each book, and work out how many of its copies are
  // available.  Store these in a list [<book>, count]
  let updatedBooks = [];
  for (book of document.querySelectorAll('#books .book')) {
    const availability = bookAvailability[book.getAttribute('data-book-id')];

    if (availability.locallyAvailableCopies === 0) {
      book.classList.add("no_local_copies");
    } else {
      book.classList.remove("no_local_copies");
    }

    const title = book.getAttribute('data-book-title');
    const year = book.getAttribute('data-book-year');

    book.querySelector('.availability').innerHTML = getAvailabilityInfo(availability);

    for (tr of book.querySelectorAll('.availability tr')) {
      if (availability.locallyAvailableLocations.includes(tr.getAttribute('data-av-location')) && tr.getAttribute('data-av-status') === 'Available') {
        tr.classList.remove('unavailable');
      } else {
        tr.classList.add('unavailable');
      }
    }

    updatedBooks.push({ book, title, year, locallyAvailableCopies: availability.locallyAvailableCopies });
  }

  // Sort the books so those with the most copies are at the top.
  // If two books have the same number of copies, arbitrarily sort
  // by title.
  updatedBooks.sort(function(a, b) {
    if (a.locallyAvailableCopies === b.locallyAvailableCopies && a.title === b.title) {
      return Number(b.year) - Number(a.year)
    } else if (a.locallyAvailableCopies === b.locallyAvailableCopies) {
      return a.title > b.title ? 1 : -1;
    } else {
      return b.locallyAvailableCopies - a.locallyAvailableCopies;
    }
  });

  let elements = document.createDocumentFragment();
  for (book of updatedBooks) {
    elements.appendChild(book.book.cloneNode(true));
  }

  document.querySelector('#books').innerHTML = null;
  document.querySelector('#books').appendChild(elements);

  for (book of document.querySelectorAll('#books .book')) {
    book.style.display = "grid";
  }

  if (selectedBranches.length > 0) {
document.querySelector('#selectedBranchCount').innerHTML = `(${selectedBranches.length} selected)`
  } else {
    document.querySelector('#selectedBranchCount').innerHTML = '';
  }
}
